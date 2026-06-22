#include "urma_failure_321.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure321> g_urma("urma_321");

bool UrmaFailure321::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_import_pseg") != std::string::npos &&
           message.find("No valid direct route") != std::string::npos;
}

std::string UrmaFailure321::GetName() const
{
    return "PSEG状态不满足要求导致导入PSEG失败";
}

std::string UrmaFailure321::GetRootCauseDesc() const
{
    return "bondp_import_pseg执行导入PSEG时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure321::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure321::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure321::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_pseg，No valid direct route。";
}

std::string UrmaFailure321::GetId() const
{
    return "urma_321";
}
} // namespace diag
