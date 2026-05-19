#include "urma_failure_737.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure737> g_urma("urma_737");

bool UrmaFailure737::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_cmd_delete_jfr_batch' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'bad jfr index exceed array length, bad_jfr_index:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure737::GetName() const
{
    return "urma_cmd_delete_jfr_batch 校验 JFR 业务条件不满足导致删除流程拒绝继续执行";
}

std::string UrmaFailure737::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfr_batch 在执行删除时发现 JFR "
           "的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资"
           "源关系或下发不被支持的请求。";
}

RootCause UrmaFailure737::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure737::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure737::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：bad jfr index exceed array length, bad_jfr_index";
}

std::string UrmaFailure737::GetId() const
{
    return "urma_737";
}

} // namespace diag
