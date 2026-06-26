#include "urma_failure_527.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure527> g_urma("urma_527");

bool UrmaFailure527::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfs_batch") != std::string::npos &&
           message.find("Failed to malloc buffer.") != std::string::npos;
}

std::string UrmaFailure527::GetName() const
{
    return "uint64分配失败导致删除JFS失败";
}

std::string UrmaFailure527::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfs_batch执行删除JFS前需要准备uint64，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure527::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure527::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure527::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfs_batch，Failed to malloc buffer.。";
}

std::string UrmaFailure527::GetId() const
{
    return "urma_527";
}
} // namespace diag
