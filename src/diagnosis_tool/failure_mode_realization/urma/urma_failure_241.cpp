#include "urma_failure_241.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure241> g_urma("urma_241");

bool UrmaFailure241::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jfs") != std::string::npos &&
           message.find("[DRV_ERR]Failed to create jfs, dev_name:") != std::string::npos &&
           message.find(", eid_idx:") != std::string::npos;
}

std::string UrmaFailure241::GetName() const
{
    return "下层资源创建失败导致创建JFS失败";
}

std::string UrmaFailure241::GetRootCauseDesc() const
{
    return "urma_create_jfs在创建JFS过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure241::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure241::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure241::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jfs，[DRV_ERR]Failed to create jfs, dev_name:，, eid_idx:。";
}

std::string UrmaFailure241::GetId() const
{
    return "urma_241";
}
} // namespace diag
