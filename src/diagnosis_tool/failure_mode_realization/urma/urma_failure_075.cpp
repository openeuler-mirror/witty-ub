#include "urma_failure_075.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure075> g_urma("urma_075");

bool UrmaFailure075::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_jfr_opt") != std::string::npos &&
           message.find("output length too large, out.len=") != std::string::npos &&
           message.find(", buf.len=") != std::string::npos;
}

std::string UrmaFailure075::GetName() const
{
    return "JFR状态不满足要求导致获取JFR失败";
}

std::string UrmaFailure075::GetRootCauseDesc() const
{
    return "urma_cmd_get_jfr_opt执行获取JFR时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure075::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure075::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure075::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_jfr_opt，output length too large, out.len=，, buf.len=。";
}

std::string UrmaFailure075::GetId() const
{
    return "urma_075";
}
} // namespace diag
