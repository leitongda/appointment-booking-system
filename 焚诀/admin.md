admin端：
顶部header中 消息通知 不要使用蓝紫色渐变，清将样式更改为  antd风格的样式。

重新整理需求，并制定了完整的实施方案。


检查系统中的如下情况。 制定了完整的实施方案。


http://127.0.0.1:8005/api/v1/appointments?doctor_id=1427e16a-84dc-433e-ac94-b914dcd42bf8&start_date=2026-01-01&end_date=2026-01-31&page=1&page_size=500

{
    "code": 422,
    "message": "query -> page_size: Input should be less than or equal to 100",
    "data": {
        "errors": [
            {
                "type": "less_than_equal",
                "loc": [
                    "query",
                    "page_size"
                ],
                "msg": "Input should be less than or equal to 100",
                "input": "500",
                "ctx": {
                    "le": 100
                }
            }
        ]
    }
}

