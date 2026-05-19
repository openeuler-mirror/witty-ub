#include "urma_failure_744.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure744> g_urma("urma_744");

bool UrmaFailure744::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_cmd_delete_jfc_batch' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'bad jfc index exceed array length, bad_jfc_index:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure744::GetName() const
{
    return "urma_cmd_delete_jfc_batch 校验 JFC 业务条件不满足导致删除流程拒绝继续执行";
}

std::string UrmaFailure744::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfc_batch 在执行删除时发现 JFC "
           "的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资"
           "源关系或下发不被支持的请求。";
}

RootCause UrmaFailure744::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure744::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure744::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：bad jfc index exceed array length, bad_jfc_index";
}

std::string UrmaFailure744::GetId() const
{
    return "urma_744";
}

} // namespace diag
