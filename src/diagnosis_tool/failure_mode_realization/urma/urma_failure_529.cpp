#include "urma_failure_529.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure529> g_urma("urma_529");

bool UrmaFailure529::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfs_batch") != std::string::npos &&
           message.find("bad jfs index exceed array length, bad_jfs_index:") != std::string::npos;
}

std::string UrmaFailure529::GetName() const
{
    return "JFS状态不满足要求导致删除JFS失败";
}

std::string UrmaFailure529::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfs_batch执行删除JFS时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure529::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure529::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure529::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfs_batch，bad jfs index exceed array length, "
           "bad_jfs_index:。";
}

std::string UrmaFailure529::GetId() const
{
    return "urma_529";
}
} // namespace diag
