#include "urma_failure_465.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure465> g_urma("urma_465");

bool UrmaFailure465::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_alloc_token_id_ex' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure465::GetName() const
{
    return "urma_alloc_token_id_ex 校验 context 无效导致分配流程拒绝继续执行";
}

std::string UrmaFailure465::GetRootCauseDesc() const
{
    return "urma_alloc_token_id_ex 在执行分配前发现调用方传入的 context "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure465::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure465::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure465::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure465::GetId() const
{
    return "urma_465";
}

} // namespace diag
