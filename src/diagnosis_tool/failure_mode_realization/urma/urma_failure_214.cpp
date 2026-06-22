#include "urma_failure_214.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure214> g_urma("urma_214");

bool UrmaFailure214::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_alloc_device") != std::string::npos &&
           message.find("snprintf failed") != std::string::npos;
}

std::string UrmaFailure214::GetName() const
{
    return "分配设备执行失败导致分配设备失败";
}

std::string UrmaFailure214::GetRootCauseDesc() const
{
    return "urma_alloc_device执行分配设备时依赖的分配设备步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure214::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure214::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure214::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_device，snprintf failed。";
}

std::string UrmaFailure214::GetId() const
{
    return "urma_214";
}
} // namespace diag
