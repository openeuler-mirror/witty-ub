#include "urma_failure_333.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure333> g_urma("urma_333");

bool UrmaFailure333::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_unregister_seg") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure333::GetName() const
{
    return "tseg、URMA context、dev_fd无效导致注销Segment失败";
}

std::string UrmaFailure333::GetRootCauseDesc() const
{
    return "urma_cmd_unregister_seg用于注销Segment，调用方传入的tseg、URMA "
           "context、dev_fd不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure333::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure333::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure333::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_unregister_seg，Invalid parameter。";
}

std::string UrmaFailure333::GetId() const
{
    return "urma_333";
}
} // namespace diag
