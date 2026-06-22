#include "urma_failure_727.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure727> g_urma("urma_727");

bool UrmaFailure727::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_active_jfr") != std::string::npos &&
           message.find("Failed to exec ops->active_jfr.") != std::string::npos;
}

std::string UrmaFailure727::GetName() const
{
    return "激活JFR执行失败导致激活JFR失败";
}

std::string UrmaFailure727::GetRootCauseDesc() const
{
    return "urma_active_jfr执行激活JFR时依赖的激活JFR步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure727::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure727::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure727::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfr，Failed to exec ops->active_jfr.。";
}

std::string UrmaFailure727::GetId() const
{
    return "urma_727";
}
} // namespace diag
