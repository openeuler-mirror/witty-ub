#include "urma_failure_704.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure704> g_urma("urma_704");

bool UrmaFailure704::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_user_ctl") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure704::GetName() const
{
    return "URMA context、in、out无效导致USER、CTL失败";
}

std::string UrmaFailure704::GetRootCauseDesc() const
{
    return "urma_cmd_user_ctl用于USER、CTL，调用方传入的URMA context、in、out不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure704::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure704::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure704::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_user_ctl，Invalid parameter。";
}

std::string UrmaFailure704::GetId() const
{
    return "urma_704";
}
} // namespace diag
