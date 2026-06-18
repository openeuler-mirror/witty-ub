#include "urma_failure_702.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure702> g_urma("urma_702");

bool UrmaFailure702::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_active_jetty") != std::string::npos &&
           message.find("Invalid flag.") != std::string::npos;
}

std::string UrmaFailure702::GetName() const
{
    return "Jetty状态不满足要求导致激活Jetty失败";
}

std::string UrmaFailure702::GetRootCauseDesc() const
{
    return "urma_cmd_active_jetty执行激活Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure702::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure702::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure702::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_active_jetty，Invalid flag.。";
}

std::string UrmaFailure702::GetId() const
{
    return "urma_702";
}
} // namespace diag
