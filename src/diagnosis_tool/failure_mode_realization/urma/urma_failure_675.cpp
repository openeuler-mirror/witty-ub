#include "urma_failure_675.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure675> g_urma("urma_675");

bool UrmaFailure675::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_ack_async_event") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure675::GetName() const
{
    return "priv无效导致ackACK、event失败";
}

std::string UrmaFailure675::GetRootCauseDesc() const
{
    return "bondp_ack_async_event用于ackACK、event，调用方传入的priv不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure675::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure675::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure675::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_ack_async_event，Invalid parameter。";
}

std::string UrmaFailure675::GetId() const
{
    return "urma_675";
}
} // namespace diag
