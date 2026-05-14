#include "urma_failure_734.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure734> g_urma("urma_734");

bool UrmaFailure734::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_cmd_delete_jfr_batch' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure734::GetName() const
{
    return "urma_cmd_delete_jfr_batch 校验 JFR 无效导致删除流程拒绝继续执行";
}

std::string UrmaFailure734::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfr_batch 在执行删除前发现调用方传入的 JFR "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure734::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure734::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure734::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure734::GetId() const
{
    return "urma_734";
}

} // namespace diag
