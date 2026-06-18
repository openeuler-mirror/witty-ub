#include "urma_failure_002.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure002> g_urma("urma_002");

bool UrmaFailure002::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("init_active_indices") != std::string::npos &&
           message.find("Invalid port_count:") != std::string::npos;
}

std::string UrmaFailure002::GetName() const
{
    return "indices状态不满足要求导致初始化indices失败";
}

std::string UrmaFailure002::GetRootCauseDesc() const
{
    return "init_active_indices执行初始化indices时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure002::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure002::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure002::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：init_active_indices，Invalid port_count:。";
}

std::string UrmaFailure002::GetId() const
{
    return "urma_002";
}
} // namespace diag
