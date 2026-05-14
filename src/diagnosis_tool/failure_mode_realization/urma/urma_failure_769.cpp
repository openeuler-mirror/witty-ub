#include "urma_failure_769.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure769> g_urma("urma_769");

bool UrmaFailure769::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_delete_jfs' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'jfs is deactived, can not delete')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure769::GetName() const
{
    return "urma_delete_jfs 执行删除 JFS 失败导致当前资源状态无法推进";
}

std::string UrmaFailure769::GetRootCauseDesc() const
{
    return "urma_delete_jfs 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure769::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure769::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure769::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：jfs is deactived, can not delete";
}

std::string UrmaFailure769::GetId() const
{
    return "urma_769";
}

} // namespace diag
