#include "urma_failure_445.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure445> g_urma("urma_445");

bool UrmaFailure445::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jfc") != std::string::npos &&
           message.find("[DRV_ERR]Failed to create jfc, dev_name:") != std::string::npos &&
           message.find(", eid_idx:") != std::string::npos;
}

std::string UrmaFailure445::GetName() const
{
    return "下层资源创建失败导致创建JFC失败";
}

std::string UrmaFailure445::GetRootCauseDesc() const
{
    return "urma_create_jfc在创建JFC过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure445::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure445::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure445::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jfc，[DRV_ERR]Failed to create jfc, dev_name:，, eid_idx:。";
}

std::string UrmaFailure445::GetId() const
{
    return "urma_445";
}
} // namespace diag
