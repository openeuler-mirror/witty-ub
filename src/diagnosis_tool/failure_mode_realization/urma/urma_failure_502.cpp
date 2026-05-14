#include "urma_failure_502.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure502> g_urma("urma_502");

bool UrmaFailure502::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'get_topo_info_from_ko' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to get topo info, change to general mode')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure502::GetName() const
{
    return "get_topo_info_from_ko 执行获取 context 失败导致当前资源状态无法推进";
}

std::string UrmaFailure502::GetRootCauseDesc() const
{
    return "get_topo_info_from_ko 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure502::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure502::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure502::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to get topo info, change to general mode";
}

std::string UrmaFailure502::GetId() const
{
    return "urma_502";
}

} // namespace diag
