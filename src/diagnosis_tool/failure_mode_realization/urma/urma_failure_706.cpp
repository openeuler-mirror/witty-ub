#include "urma_failure_706.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure706> g_urma("urma_706");

bool UrmaFailure706::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_check_opt_valid") != std::string::npos &&
           message.find("invalid opt len") != std::string::npos;
}

std::string UrmaFailure706::GetName() const
{
    return "valid状态不满足要求导致校验valid失败";
}

std::string UrmaFailure706::GetRootCauseDesc() const
{
    return "urma_check_opt_valid执行校验valid时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure706::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure706::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure706::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_opt_valid，invalid opt len。";
}

std::string UrmaFailure706::GetId() const
{
    return "urma_706";
}
} // namespace diag
