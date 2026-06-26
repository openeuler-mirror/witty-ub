#include "urma_failure_097.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure097> g_urma("urma_097");

bool UrmaFailure097::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_import_jfr") != std::string::npos &&
           message.find("Token value must be set when token policy is not URMA_TOKEN_NONE.") != std::string::npos;
}

std::string UrmaFailure097::GetName() const
{
    return "JFR状态不满足要求导致导入JFR失败";
}

std::string UrmaFailure097::GetRootCauseDesc() const
{
    return "urma_import_jfr执行导入JFR时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure097::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure097::GetFixSuggDesc() const
{
    return "UDMA错误定界；建链交换信息失败，可重试";
}

std::string UrmaFailure097::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_import_jfr，Token value must be set when token policy is not "
           "URMA_TOKEN_N"
           "ONE.。";
}

std::string UrmaFailure097::GetId() const
{
    return "urma_097";
}
} // namespace diag
