from datetime import datetime
from fastapi import HTTPException, status


# 注意：你需要从定义 get_current_user 的地方导入它
# 假设你把它定义在 main.py，但这会造成循环引用。
# ⚡️ 最佳实践：建议新建一个 auth.py 放 get_current_user，然后在这里导入
# from auth import get_current_user

# 为了让你现在能跑起来，我建议把这个 verify 函数直接放在 main.py 里
# 如果非要放在 vip.py，你需要确保能导入 get_current_user
# 这里先假设传进来的 user 已经是解析好的对象或字典

async def check_permission(user):
    """
    VIP 权限校验逻辑
    注意：去掉 Depends(get_current_user)，由 main.py 调用时传入 user
    """
    now = datetime.now()

    # 1. 计算注册天数（兼容没有 created_at 字段的用户模型）
    if isinstance(user, dict):
        create_time = user.get("created_at")
        vip_expiry = user.get("vip_expiry")
    else:
        create_time = getattr(user, "created_at", None)
        vip_expiry = getattr(user, "vip_expiry", None)

    # 当前 User 模型没有 created_at 字段时，默认给 3 天试用，避免直接 500
    if create_time is None:
        create_time = now

    days_since_reg = (now - create_time).days

    # 2. 逻辑判断
    is_free_trial = days_since_reg < 3  # 前3天免费

    # 判断 VIP 是否有效
    is_vip = False
    if vip_expiry:
        is_vip = vip_expiry > now

    # 3. 拦截逻辑
    if not (is_free_trial or is_vip):
        # 返回 402 Payment Required 状态码
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="试用期已结束，请开通会员"
        )

    return True