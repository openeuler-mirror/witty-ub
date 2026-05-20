#include "urma_failure_730.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure730> g_urma("urma_730");

bool UrmaFailure730::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_cmd_delete_jfs_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'bad jfs index exceed array length, bad_jfs_index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure730::GetName() const
{
    return "urma_cmd_delete_jfs_batch 校验 JFS 业务条件不满足导致删除流程拒绝继续执行";
}

std::string UrmaFailure730::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfs_batch 在执行删除时发现 JFS "
           "的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资"
           "源关系或下发不被支持的请求。";
}

RootCause UrmaFailure730::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure730::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure730::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：bad jfs index exceed array length, bad_jfs_index";
}

std::string UrmaFailure730::GetId() const
{
    return "urma_730";
}

} // namespace diag
