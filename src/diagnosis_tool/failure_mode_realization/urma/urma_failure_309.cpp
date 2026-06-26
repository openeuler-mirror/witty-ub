#include "urma_failure_309.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure309> g_urma("urma_309");

bool UrmaFailure309::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_pseg") != std::string::npos &&
           message.find("Invalid segment address for bondp seg") != std::string::npos;
}

std::string UrmaFailure309::GetName() const
{
    return "PSEG状态不满足要求导致创建PSEG失败";
}

std::string UrmaFailure309::GetRootCauseDesc() const
{
    return "bondp_create_pseg执行创建PSEG时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure309::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure309::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure309::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_pseg，Invalid segment address for bondp seg。";
}

std::string UrmaFailure309::GetId() const
{
    return "urma_309";
}
} // namespace diag
