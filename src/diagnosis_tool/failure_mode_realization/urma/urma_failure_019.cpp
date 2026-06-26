#include "urma_failure_019.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure019> g_urma("urma_019");

bool UrmaFailure019::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_health_check_ctx") != std::string::npos &&
           message.find("Failed to init health event lock") != std::string::npos;
}

std::string UrmaFailure019::GetName() const
{
    return "创建health、context执行失败导致创建health、context失败";
}

std::string UrmaFailure019::GetRootCauseDesc() const
{
    return "bondp_create_health_check_"
           "ctx执行创建health、context时依赖的创建health、context步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure019::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure019::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure019::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_health_check_ctx，Failed to init health event lock。";
}

std::string UrmaFailure019::GetId() const
{
    return "urma_019";
}
} // namespace diag
