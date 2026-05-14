#include "urma_failure_407.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure407> g_urma("urma_407");

bool UrmaFailure407::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_alloc_jfr' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter, trans_mode')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure407::GetName() const
{
    return "urma_alloc_jfr 校验 JFR 无效导致分配流程拒绝继续执行";
}

std::string UrmaFailure407::GetRootCauseDesc() const
{
    return "urma_alloc_jfr 在执行分配前发现调用方传入的 JFR 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure407::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure407::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure407::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter, trans_mode";
}

std::string UrmaFailure407::GetId() const
{
    return "urma_407";
}

} // namespace diag
