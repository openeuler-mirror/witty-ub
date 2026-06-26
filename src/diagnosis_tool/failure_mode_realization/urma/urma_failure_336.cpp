#include "urma_failure_336.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure336> g_urma("urma_336");

bool UrmaFailure336::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_unimport_seg") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure336::GetName() const
{
    return "tseg、URMA context、dev_fd无效导致取消导入Segment失败";
}

std::string UrmaFailure336::GetRootCauseDesc() const
{
    return "urma_cmd_unimport_seg用于取消导入Segment，调用方传入的tseg、URMA "
           "context、dev_fd不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure336::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure336::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure336::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_unimport_seg，Invalid parameter。";
}

std::string UrmaFailure336::GetId() const
{
    return "urma_336";
}
} // namespace diag
