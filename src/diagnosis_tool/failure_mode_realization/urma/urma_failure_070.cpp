#include "urma_failure_070.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure070> g_urma("urma_070");

bool UrmaFailure070::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_jfs_opt") != std::string::npos &&
           message.find("output length too large, out.len=") != std::string::npos &&
           message.find(", buf.len=") != std::string::npos;
}

std::string UrmaFailure070::GetName() const
{
    return "JFS状态不满足要求导致获取JFS失败";
}

std::string UrmaFailure070::GetRootCauseDesc() const
{
    return "urma_cmd_get_jfs_opt执行获取JFS时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure070::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure070::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure070::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_jfs_opt，output length too large, out.len=，, buf.len=。";
}

std::string UrmaFailure070::GetId() const
{
    return "urma_070";
}
} // namespace diag
