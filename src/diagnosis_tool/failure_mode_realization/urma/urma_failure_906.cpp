#include "urma_failure_906.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure906> g_urma("urma_906");

bool UrmaFailure906::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'check_valid_sgl' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'sge is a null pointer')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure906::GetName() const
{
    return "check_valid_sgl 校验 SGL 无效导致校验流程拒绝继续执行";
}

std::string UrmaFailure906::GetRootCauseDesc() const
{
    return "check_valid_sgl 在执行校验前发现调用方传入的 SGL 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure906::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure906::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure906::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：sge is a null pointer";
}

std::string UrmaFailure906::GetId() const
{
    return "urma_906";
}

} // namespace diag
