#include "urma_failure_295.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure295> g_urma("urma_295");

bool UrmaFailure295::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'deepcopy_cas_wr' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to copy src sge')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure295::GetName() const
{
    return "deepcopy_cas_wr 执行复制 WR 失败导致当前资源状态无法推进";
}

std::string UrmaFailure295::GetRootCauseDesc() const
{
    return "deepcopy_cas_wr 调用下层 provider、bond 组件或系统接口处理 WR 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure295::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure295::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure295::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to copy src sge";
}

std::string UrmaFailure295::GetId() const
{
    return "urma_295";
}

} // namespace diag
