#include "urma_failure_429.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure429> g_urma("urma_429");

bool UrmaFailure429::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_jfc_opt") != std::string::npos &&
           message.find("Invalid out buffer from kernel.") != std::string::npos;
}

std::string UrmaFailure429::GetName() const
{
    return "JFC状态不满足要求导致获取JFC失败";
}

std::string UrmaFailure429::GetRootCauseDesc() const
{
    return "urma_cmd_get_jfc_opt执行获取JFC时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure429::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure429::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure429::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_jfc_opt，Invalid out buffer from kernel.。";
}

std::string UrmaFailure429::GetId() const
{
    return "urma_429";
}
} // namespace diag
