"""
患者数据脱敏工具

提供患者数据的脱敏转换函数，用于 API 返回。
所有返回给前端的患者数据都应通过此工具处理。
"""
from app.utils.masking import get_masked_phone, get_masked_id_card


def mask_patient_data(patient_dict: dict) -> dict:
    """对患者数据字典进行脱敏处理

    Args:
        patient_dict: 包含患者数据的字典（需包含 phone/idCard 字段）

    Returns:
        脱敏后的字典（原地修改）
    """
    # 脱敏手机号
    if "phone" in patient_dict and patient_dict["phone"]:
        patient_dict["phone"] = get_masked_phone(None, patient_dict["phone"])

    # 脱敏身份证号
    if "idCard" in patient_dict and patient_dict["idCard"]:
        patient_dict["idCard"] = get_masked_id_card(None, patient_dict["idCard"])

    # 脱敏 userPhone（如果有）
    if "userPhone" in patient_dict and patient_dict["userPhone"]:
        patient_dict["userPhone"] = get_masked_phone(None, patient_dict["userPhone"])

    return patient_dict


def mask_patient_list(patients: list[dict]) -> list[dict]:
    """对患者列表进行批量脱敏

    Args:
        patients: 患者数据字典列表

    Returns:
        脱敏后的列表
    """
    return [mask_patient_data(p) for p in patients]
