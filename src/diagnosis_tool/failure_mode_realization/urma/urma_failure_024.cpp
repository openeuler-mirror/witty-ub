#include "urma_failure_024.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure024> g_urma("urma_024");

bool UrmaFailure024::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'get_new_jfs_wr' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'unsupport opcode')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure024::GetName() const
{
    return "get_new_jfs_wr 执行获取 JFS 失败导致当前资源状态无法推进";
}

std::string UrmaFailure024::GetRootCauseDesc() const
{
    return "get_new_jfs_wr 调用下层 provider、bond 组件或系统接口处理 JFS 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure024::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure024::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure024::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：unsupport opcode";
}

std::string UrmaFailure024::GetId() const
{
    return "urma_024";
}

} // namespace diag
