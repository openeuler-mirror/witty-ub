#include "urma_failure_415.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure415> g_urma("urma_415");

bool UrmaFailure415::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_create_jfce' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure415::GetName() const
{
    return "urma_create_jfce 校验 context 无效导致创建流程拒绝继续执行";
}

std::string UrmaFailure415::GetRootCauseDesc() const
{
    return "urma_create_jfce 在执行创建前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure415::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure415::GetFixSuggDesc() const
{
    return "当前预期不会出现，如果 fd 超规格可能导致失败，此时需要修改系统 fd 规格数，或者减小应用创建 jfce 的数量";
}

std::string UrmaFailure415::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure415::GetId() const
{
    return "urma_415";
}

} // namespace diag
