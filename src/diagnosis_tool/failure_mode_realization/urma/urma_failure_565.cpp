#include "urma_failure_565.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure565> g_urma("urma_565");

bool UrmaFailure565::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfs_batch") != std::string::npos &&
           message.find("Failed to alloc memory.") != std::string::npos;
}

std::string UrmaFailure565::GetName() const
{
    return "urma context *分配失败导致删除JFS失败";
}

std::string UrmaFailure565::GetRootCauseDesc() const
{
    return "urma_delete_jfs_batch执行删除JFS前需要准备urma context *，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure565::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure565::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure565::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfs_batch，Failed to alloc memory.。";
}

std::string UrmaFailure565::GetId() const
{
    return "urma_565";
}
} // namespace diag
