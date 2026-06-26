#include "urma_failure_493.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure493> g_urma("urma_493");

bool UrmaFailure493::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_ack_jfc") != std::string::npos && message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure493::GetName() const
{
    return "JFC、nevents、jfc_cnt无效导致ackACK、JFC失败";
}

std::string UrmaFailure493::GetRootCauseDesc() const
{
    return "urma_ack_jfc用于ackACK、JFC，调用方传入的JFC、nevents、jfc_cnt不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure493::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure493::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure493::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_ack_jfc，Invalid parameter.。";
}

std::string UrmaFailure493::GetId() const
{
    return "urma_493";
}
} // namespace diag
