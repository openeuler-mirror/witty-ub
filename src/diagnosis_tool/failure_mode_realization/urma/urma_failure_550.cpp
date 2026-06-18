#include "urma_failure_550.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure550> g_urma("urma_550");

bool UrmaFailure550::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jetty_batch") != std::string::npos &&
           message.find("jetty not from the same dev, cannot delete in a batch, index:") != std::string::npos;
}

std::string UrmaFailure550::GetName() const
{
    return "Jetty状态不满足要求导致删除Jetty失败";
}

std::string UrmaFailure550::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jetty_batch执行删除Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure550::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure550::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure550::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jetty_batch，jetty not from the same dev, cannot delete "
           "in a b"
           "atch, index:。";
}

std::string UrmaFailure550::GetId() const
{
    return "urma_550";
}
} // namespace diag
