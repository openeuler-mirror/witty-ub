#include "urma_failure_697.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure697> g_urma("urma_697");

bool UrmaFailure697::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_delete_pjfs' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to delete pjfs' | grep -F ', ret:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure697::GetName() const
{
    return "bondp_delete_pjfs 执行删除 JFS 失败导致当前资源状态无法推进";
}

std::string UrmaFailure697::GetRootCauseDesc() const
{
    return "bondp_delete_pjfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure697::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure697::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure697::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to delete pjfs , ret";
}

std::string UrmaFailure697::GetId() const
{
    return "urma_697";
}

} // namespace diag
