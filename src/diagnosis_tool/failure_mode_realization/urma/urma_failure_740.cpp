#include "urma_failure_740.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure740> g_urma("urma_740");

bool UrmaFailure740::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_ack_notify") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure740::GetName() const
{
    return "URMA context、notify无效导致ackACK、notify失败";
}

std::string UrmaFailure740::GetRootCauseDesc() const
{
    return "urma_ack_notify用于ackACK、notify，调用方传入的URMA context、notify不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure740::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure740::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure740::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_ack_notify，Invalid parameter.。";
}

std::string UrmaFailure740::GetId() const
{
    return "urma_740";
}
} // namespace diag
