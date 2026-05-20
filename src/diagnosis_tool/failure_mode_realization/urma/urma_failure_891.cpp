#include "urma_failure_891.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure891> g_urma("urma_891");

bool UrmaFailure891::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_check_seg_cfg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'token_id must set when token_id_valid is true, or must NULL when token_id_valid is false'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure891::GetName() const
{
    return "urma_check_seg_cfg 校验 segment 无效导致校验流程拒绝继续执行";
}

std::string UrmaFailure891::GetRootCauseDesc() const
{
    return "urma_check_seg_cfg 在执行校验前发现调用方传入的 segment 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure891::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure891::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure891::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：token_id must set when token_id_valid is true, or must NULL when "
           "token_id_valid is false";
}

std::string UrmaFailure891::GetId() const
{
    return "urma_891";
}

} // namespace diag
