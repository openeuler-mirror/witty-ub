#include "urma_failure_223.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure223> g_urma("urma_223");

bool UrmaFailure223::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_user_ctl_query_port") != std::string::npos &&
           message.find("Invalid jfr.") != std::string::npos;
}

std::string UrmaFailure223::GetName() const
{
    return "USER、CTL、端口状态不满足要求导致查询USER、CTL、端口失败";
}

std::string UrmaFailure223::GetRootCauseDesc() const
{
    return "bondp_user_ctl_query_"
           "port执行查询USER、CTL、端口时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure223::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure223::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure223::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_user_ctl_query_port，Invalid jfr.。";
}

std::string UrmaFailure223::GetId() const
{
    return "urma_223";
}
} // namespace diag
