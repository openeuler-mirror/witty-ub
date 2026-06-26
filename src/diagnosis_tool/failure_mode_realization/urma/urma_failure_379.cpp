#include "urma_failure_379.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure379> g_urma("urma_379");

bool UrmaFailure379::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("post_send_check_valid") != std::string::npos &&
           message.find("Try to call post_send api by invalid comp_type:") != std::string::npos;
}

std::string UrmaFailure379::GetName() const
{
    return "valid状态不满足要求导致投递valid失败";
}

std::string UrmaFailure379::GetRootCauseDesc() const
{
    return "post_send_check_valid执行投递valid时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure379::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure379::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure379::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：post_send_check_valid，Try to call post_send api by invalid "
           "comp_type:。";
}

std::string UrmaFailure379::GetId() const
{
    return "urma_379";
}
} // namespace diag
