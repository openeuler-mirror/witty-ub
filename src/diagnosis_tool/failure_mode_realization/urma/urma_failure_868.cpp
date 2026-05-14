#include "urma_failure_868.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure868> g_urma("urma_868");

bool UrmaFailure868::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'deepcopy_jfs_wr_node' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Not support opcode')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure868::GetName() const
{
    return "deepcopy_jfs_wr_node 校验 JFS 业务条件不满足导致复制流程拒绝继续执行";
}

std::string UrmaFailure868::GetRootCauseDesc() const
{
    return "deepcopy_jfs_wr_node 在执行复制时发现 JFS "
           "的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资"
           "源关系或下发不被支持的请求。";
}

RootCause UrmaFailure868::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure868::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure868::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Not support opcode";
}

std::string UrmaFailure868::GetId() const
{
    return "urma_868";
}

} // namespace diag
