"""
Tool Definitions for OpenAI Function Calling
==============================================

DESIGN CONCEPT: Function/Tool Calling
----------------------------------------
This is a KEY concept in the OpenAI Responses API.

The flow works like this:

1. User asks a question in natural language
2. We send the user's message + our SYSTEM_PROMPT + TOOL DEFINITIONS to OpenAI
3. OpenAI's model decides:
   a. It can respond directly (no tool needed) - for greetings, chit-chat, etc.
   b. It can call one or more tools - when it needs data from our database
4. If the model calls a tool, we:
   a. Execute the corresponding Python function
   b. Send the function's return value back to OpenAI
   c. OpenAI then formulates a natural language response for the user

This pattern is called "Tool-Augmented LLM" or "Function Calling."
It bridges the gap between:
  - LLM's knowledge (language understanding, conversation)
  - Our backend data (doctor schedules, availability)

We define tools with:
  - name:        The function name the model will call
  - description: Tells the model WHEN to use this tool
  - parameters:  JSON Schema describing the arguments

The model NEVER executes code - it only REQUEST tool calls.
WE (our application) execute the actual Python functions.
"""

from datetime import datetime, timedelta
from typing import Callable

from doctor_assistant.db.models import DoctorAssistantDB


def get_tool_definitions() -> list[dict]:
    """
    Returns the OpenAI-compatible tool definitions.
    
    These are sent in the API request so the model knows what tools are
    available and when to use each one.
    
    Each tool has:
      - type: Always "function" for custom functions
      - function.name: The function identifier
      - function.description: Natural language description of when to call
      - function.parameters: JSON Schema object for argument validation
    
    Returns:
        List of tool definition dicts for the OpenAI API
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_departments",
                "description": (
                    "Get a list of all medical departments/specialties "
                    "available at the clinic."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_all_doctors",
                "description": (
                    "Get a list of all doctors with their departments. "
                    "Use this when you need to show all available doctors "
                    "or help a patient choose a doctor."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_doctors_by_department",
                "description": (
                    "Find doctors for a specific medical department or "
                    "specialty. Use this when a patient describes symptoms "
                    "and you need to find the right specialist."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "department_name": {
                            "type": "string",
                            "description": (
                                "The name of the department/specialty "
                                "(e.g., Cardiology, Orthopedics, Dermatology)"
                            )
                        }
                    },
                    "required": ["department_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_doctor_by_name",
                "description": (
                    "Find a doctor by their name. Use this when a patient "
                    "specifically asks for a doctor by name."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doctor_name": {
                            "type": "string",
                            "description": (
                                "The full or partial name of the doctor "
                                "(e.g., 'Dr. Sharma', 'Dr. Singh')"
                            )
                        }
                    },
                    "required": ["doctor_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_available_slots",
                "description": (
                    "Check available appointment slots for a specific doctor "
                    "on a specific date. Returns available 30-minute time slots. "
                    "Use this before suggesting or booking an appointment."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doctor_id": {
                            "type": "integer",
                            "description": "The doctor's ID number"
                        },
                        "date": {
                            "type": "string",
                            "description": (
                                "The date to check in YYYY-MM-DD format "
                                "(e.g., '2026-06-06')"
                            )
                        }
                    },
                    "required": ["doctor_id", "date"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": (
                    "Book an appointment for a patient with a doctor. "
                    "This will create a patient record and mark the time "
                    "slot as unavailable for future bookings. "
                    "Call this ONLY after the patient has confirmed "
                    "they want a specific time slot."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "doctor_id": {
                            "type": "integer",
                            "description": "The doctor's ID number"
                        },
                        "patient_name": {
                            "type": "string",
                            "description": "The patient's full name"
                        },
                        "patient_phone": {
                            "type": "string",
                            "description": (
                                "The patient's phone number "
                                "(optional but recommended)"
                            )
                        },
                        "date": {
                            "type": "string",
                            "description": (
                                "Appointment date in YYYY-MM-DD format"
                            )
                        },
                        "start_time": {
                            "type": "string",
                            "description": (
                                "Appointment start time in HH:MM format "
                                "(e.g., '10:00')"
                            )
                        },
                        "end_time": {
                            "type": "string",
                            "description": (
                                "Appointment end time in HH:MM format "
                                "(e.g., '10:30')"
                            )
                        },
                        "reason": {
                            "type": "string",
                            "description": (
                                "Brief reason for the visit / symptoms "
                                "(optional)"
                            )
                        }
                    },
                    "required": [
                        "doctor_id", "patient_name", "date",
                        "start_time", "end_time"
                    ]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "suggest_alternative_doctor",
                "description": (
                    "When a doctor is not available, suggest another doctor "
                    "in the same department. Use this to find alternatives "
                    "for the patient."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "department_name": {
                            "type": "string",
                            "description": (
                                "The department/specialty name to search in"
                            )
                        },
                        "unavailable_doctor_id": {
                            "type": "integer",
                            "description": (
                                "The ID of the doctor who is unavailable"
                            )
                        }
                    },
                    "required": ["department_name", "unavailable_doctor_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_today_date",
                "description": (
                    "Get today's date in YYYY-MM-DD format. "
                    "Use this when you need the current date to check "
                    "availability or interpret relative dates like 'tomorrow' "
                    "or 'today'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]


def create_tool_handlers(db: DoctorAssistantDB) -> dict[str, Callable]:
    """
    Create the mapping from tool names to actual handler functions.
    
    This is the "dispatcher" that routes tool call requests from OpenAI
    to the correct Python function that interacts with the database.
    
    DESIGN CONCEPT: Handler Pattern
    -------------------------------
    Each function follows the same contract:
      - Takes **kwargs (keyword arguments parsed from OpenAI's tool call)
      - Returns a dict/list/string that can be sent back to the LLM
    
    Args:
        db: Database instance to query/modify
        
    Returns:
        Dict mapping tool name strings to handler functions
    """
    
    def handle_get_departments(**kwargs) -> str:
        departments = db.get_departments()
        if not departments:
            return "No departments found."
        result = "Available departments:\n"
        for dept in departments:
            result += f"- {dept['name']}: {dept['description']}\n"
        return result

    def handle_get_all_doctors(**kwargs) -> str:
        doctors = db.get_all_doctors()
        if not doctors:
            return "No doctors found."
        result = "All doctors:\n"
        for doc in doctors:
            result += (
                f"- {doc['name']} ({doc['department']})\n"
            )
        return result

    def handle_get_doctors_by_department(**kwargs) -> str:
        dept = kwargs.get("department_name", "")
        doctors = db.get_doctors_by_department(dept)
        if not doctors:
            return (
                f"No doctors found in department matching '{dept}'. "
                "Please check the available departments."
            )
        result = f"Doctors in {dept}:\n"
        for doc in doctors:
            result += f"- ID: {doc['id']}, {doc['name']}\n"
        return result

    def handle_get_doctor_by_name(**kwargs) -> str:
        name = kwargs.get("doctor_name", "")
        doctor = db.get_doctor_by_name(name)
        if not doctor:
            return f"No doctor found matching '{name}'."
        return (
            f"Doctor found:\n"
            f"  ID: {doctor['id']}\n"
            f"  Name: {doctor['name']}\n"
            f"  Department: {doctor['department']}\n"
            f"  Phone: {doctor.get('phone', 'N/A')}\n"
            f"  Email: {doctor.get('email', 'N/A')}"
        )

    def handle_get_available_slots(**kwargs) -> str:
        doctor_id = kwargs.get("doctor_id")
        date_str = kwargs.get("date")
        
        if not doctor_id or not date_str:
            return "Error: Both doctor_id and date are required."
        
        slots = db.get_available_slots(doctor_id, date_str)
        
        if not slots:
            # Check if the doctor exists at all
            all_doctors = db.get_all_doctors()
            doctor_info = next((d for d in all_doctors if d["id"] == doctor_id), None)
            
            if doctor_info:
                return (
                    f"{doctor_info['name']} is not available on {date_str}. "
                    "No available slots found."
                )
            else:
                return f"No doctor found with ID {doctor_id}."
        
        result = f"Available slots for doctor ID {doctor_id} on {date_str}:\n"
        for slot in slots:
            result += f"- {slot['start_time']} to {slot['end_time']}\n"
        return result.strip()

    def handle_book_appointment(**kwargs) -> str:
        doctor_id = kwargs.get("doctor_id")
        patient_name = kwargs.get("patient_name")
        patient_phone = kwargs.get("patient_phone", "")
        date_str = kwargs.get("date")
        start_time = kwargs.get("start_time")
        end_time = kwargs.get("end_time")
        reason = kwargs.get("reason", "")
        
        if not all([doctor_id, patient_name, date_str, start_time, end_time]):
            return "Error: Missing required fields for booking."
        
        result = db.book_appointment(
            doctor_id=doctor_id,
            patient_name=patient_name,
            patient_phone=patient_phone,
            date_str=date_str,
            start_time=start_time,
            end_time=end_time,
            reason=reason
        )
        
        if result["success"]:
            return (
                f"SUCCESS: Appointment booked!\n"
                f"  Appointment ID: {result['appointment_id']}\n"
                f"  Patient: {result['patient_name']}\n"
                f"  Doctor: {result['doctor_name']}\n"
                f"  Date: {result['date']}\n"
                f"  Time: {result['start_time']} - {result['end_time']}\n"
                f"  Message: {result['message']}"
            )
        else:
            return f"FAILED: {result['message']}"

    def handle_suggest_alternative_doctor(**kwargs) -> str:
        department = kwargs.get("department_name", "")
        unavailable_id = kwargs.get("unavailable_doctor_id")
        
        doctors = db.get_doctors_by_department(department)
        
        # Filter out the unavailable doctor
        alternatives = [
            d for d in doctors if d["id"] != unavailable_id
        ]
        
        if not alternatives:
            return (
                f"No alternative doctors found in {department} "
                "(all doctors in this department are unavailable or "
                "there is only one doctor)."
            )
        
        result = f"Alternative doctors in {department}:\n"
        for doc in alternatives:
            result += f"- ID: {doc['id']}, {doc['name']}\n"
        return result.strip()

    def handle_get_today_date(**kwargs) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        day_name = datetime.now().strftime("%A")
        return f"Today's date is {today} ({day_name})."

    # Map tool names to handler functions
    return {
        "get_departments": handle_get_departments,
        "get_all_doctors": handle_get_all_doctors,
        "get_doctors_by_department": handle_get_doctors_by_department,
        "get_doctor_by_name": handle_get_doctor_by_name,
        "get_available_slots": handle_get_available_slots,
        "book_appointment": handle_book_appointment,
        "suggest_alternative_doctor": handle_suggest_alternative_doctor,
        "get_today_date": handle_get_today_date,
    }