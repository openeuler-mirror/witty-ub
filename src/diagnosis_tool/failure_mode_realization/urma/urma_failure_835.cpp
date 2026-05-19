#include "urma_failure_835.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure835> g_urma("urma_835");

bool UrmaFailure835::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_add_jfs_p_vjetty_id_info' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to add p_vjfs_id[' | grep -F ']: ret:' | grep -F ', p_jfs_id:' | grep -F ', v_jfs_id:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure835::GetName() const
{
    return "bondp_add_jfs_p_vjetty_id_info 执行处理 Jetty 失败导致当前资源状态无法推进";
}

std::string UrmaFailure835::GetRootCauseDesc() const
{
    return "bondp_add_jfs_p_vjetty_id_info 调用下层 provider、bond 组件或系统接口处理 Jetty 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure835::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure835::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure835::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to add p_vjfs_id[]: ret: , p_jfs_id: , v_jfs_id";
}

std::string UrmaFailure835::GetId() const
{
    return "urma_835";
}

} // namespace diag
