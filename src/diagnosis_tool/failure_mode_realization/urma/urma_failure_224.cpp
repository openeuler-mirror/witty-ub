#include "urma_failure_224.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure224> g_urma("urma_224");

bool UrmaFailure224::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_user_ctl_query_port") != std::string::npos &&
           message.find("The object does not belong to current context.") != std::string::npos;
}

std::string UrmaFailure224::GetName() const
{
    return "USER、CTL、端口状态不满足要求导致查询USER、CTL、端口失败";
}

std::string UrmaFailure224::GetRootCauseDesc() const
{
    return "bondp_user_ctl_query_"
           "port执行查询USER、CTL、端口时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure224::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure224::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure224::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_user_ctl_query_port，The object does not belong to current "
           "context.。";
}

std::string UrmaFailure224::GetId() const
{
    return "urma_224";
}
} // namespace diag
