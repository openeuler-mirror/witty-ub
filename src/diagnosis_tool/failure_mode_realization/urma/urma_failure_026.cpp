#include "urma_failure_026.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure026> g_urma("urma_026");

bool UrmaFailure026::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'get_bonding_eid_by_target_eid' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid param')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure026::GetName() const
{
    return "get_bonding_eid_by_target_eid 校验 EID 无效导致获取流程拒绝继续执行";
}

std::string UrmaFailure026::GetRootCauseDesc() const
{
    return "get_bonding_eid_by_target_eid 在执行获取前发现调用方传入的 EID "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure026::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure026::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure026::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid param";
}

std::string UrmaFailure026::GetId() const
{
    return "urma_026";
}

} // namespace diag
