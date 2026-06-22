#include "urma_failure_469.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure469> g_urma("urma_469");

bool UrmaFailure469::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_active_jfc") != std::string::npos &&
           message.find("Failed to exec ops->active_jfc.") != std::string::npos;
}

std::string UrmaFailure469::GetName() const
{
    return "激活JFC执行失败导致激活JFC失败";
}

std::string UrmaFailure469::GetRootCauseDesc() const
{
    return "urma_active_jfc执行激活JFC时依赖的激活JFC步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure469::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure469::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure469::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfc，Failed to exec ops->active_jfc.。";
}

std::string UrmaFailure469::GetId() const
{
    return "urma_469";
}
} // namespace diag
