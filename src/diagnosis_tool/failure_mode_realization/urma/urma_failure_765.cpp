#include "urma_failure_765.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure765> g_urma("urma_765");

bool UrmaFailure765::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_free_jfs' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'jfs still actived, please deactived first')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure765::GetName() const
{
    return "urma_free_jfs 执行释放 JFS 失败导致当前资源状态无法推进";
}

std::string UrmaFailure765::GetRootCauseDesc() const
{
    return "urma_free_jfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure765::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure765::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure765::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：jfs still actived, please deactived first";
}

std::string UrmaFailure765::GetId() const
{
    return "urma_765";
}

} // namespace diag
