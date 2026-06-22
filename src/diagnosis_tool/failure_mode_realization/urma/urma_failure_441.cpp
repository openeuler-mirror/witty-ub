#include "urma_failure_441.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure441> g_urma("urma_441");

bool UrmaFailure441::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_ack_jfc") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure441::GetName() const
{
    return "JFC、nevents、jfc_cnt无效导致ACK、JFC失败";
}

std::string UrmaFailure441::GetRootCauseDesc() const
{
    return "urma_cmd_ack_jfc用于ACK、JFC，调用方传入的JFC、nevents、jfc_cnt不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure441::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure441::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure441::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_ack_jfc，Invalid parameter。";
}

std::string UrmaFailure441::GetId() const
{
    return "urma_441";
}
} // namespace diag
