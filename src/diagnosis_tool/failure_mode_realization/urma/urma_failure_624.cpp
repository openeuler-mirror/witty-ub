#include "urma_failure_624.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure624> g_urma("urma_624");

bool UrmaFailure624::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_jfr_opt") != std::string::npos &&
           message.find("Invalid out buffer from kernel.") != std::string::npos;
}

std::string UrmaFailure624::GetName() const
{
    return "JFR状态不满足要求导致获取JFR失败";
}

std::string UrmaFailure624::GetRootCauseDesc() const
{
    return "urma_cmd_get_jfr_opt执行获取JFR时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure624::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure624::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure624::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_jfr_opt，Invalid out buffer from kernel.。";
}

std::string UrmaFailure624::GetId() const
{
    return "urma_624";
}
} // namespace diag
