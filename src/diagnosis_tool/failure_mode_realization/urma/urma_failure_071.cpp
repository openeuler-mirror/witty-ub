#include "urma_failure_071.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure071> g_urma("urma_071");

bool UrmaFailure071::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_jfc_opt") != std::string::npos &&
           message.find("output length too large, out.len=") != std::string::npos &&
           message.find(", buf.len=") != std::string::npos;
}

std::string UrmaFailure071::GetName() const
{
    return "JFC状态不满足要求导致获取JFC失败";
}

std::string UrmaFailure071::GetRootCauseDesc() const
{
    return "urma_cmd_get_jfc_opt执行获取JFC时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure071::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure071::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure071::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_jfc_opt，output length too large, out.len=，, buf.len=。";
}

std::string UrmaFailure071::GetId() const
{
    return "urma_071";
}
} // namespace diag
