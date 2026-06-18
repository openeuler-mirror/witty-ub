#include "urma_failure_747.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure747> g_urma("urma_747");

bool UrmaFailure747::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_user_ctl") != std::string::npos &&
           message.find("Failed to excecute user_ctl, ret:") != std::string::npos;
}

std::string UrmaFailure747::GetName() const
{
    return "userUSER、CTL执行失败导致userUSER、CTL失败";
}

std::string UrmaFailure747::GetRootCauseDesc() const
{
    return "urma_user_ctl执行userUSER、CTL时依赖的userUSER、CTL步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure747::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure747::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure747::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_user_ctl，Failed to excecute user_ctl, ret:。";
}

std::string UrmaFailure747::GetId() const
{
    return "urma_747";
}
} // namespace diag
