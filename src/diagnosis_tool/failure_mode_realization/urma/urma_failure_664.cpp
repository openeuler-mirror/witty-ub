#include "urma_failure_664.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure664> g_urma("urma_664");

bool UrmaFailure664::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_context_opt") != std::string::npos &&
           message.find("Cannot set aggregated mode for non-aggregated device.") != std::string::npos;
}

std::string UrmaFailure664::GetName() const
{
    return "context状态不满足要求导致设置context失败";
}

std::string UrmaFailure664::GetRootCauseDesc() const
{
    return "urma_set_context_opt执行设置context时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure664::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure664::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure664::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_context_opt，Cannot set aggregated mode for non-aggregated "
           "device.。";
}

std::string UrmaFailure664::GetId() const
{
    return "urma_664";
}
} // namespace diag
