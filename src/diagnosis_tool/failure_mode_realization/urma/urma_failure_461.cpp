#include "urma_failure_461.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure461> g_urma("urma_461");

bool UrmaFailure461::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_set_jfc_opt") != std::string::npos &&
           message.find("invalid opt id or opt len") != std::string::npos;
}

std::string UrmaFailure461::GetName() const
{
    return "JFC状态不满足要求导致设置JFC失败";
}

std::string UrmaFailure461::GetRootCauseDesc() const
{
    return "urma_set_jfc_opt执行设置JFC时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure461::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure461::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure461::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfc_opt，invalid opt id or opt len。";
}

std::string UrmaFailure461::GetId() const
{
    return "urma_461";
}
} // namespace diag
