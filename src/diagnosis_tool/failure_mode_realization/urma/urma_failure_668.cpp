#include "urma_failure_668.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure668> g_urma("urma_668");

bool UrmaFailure668::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_modify_jfs") != std::string::npos &&
           message.find("modify pjfs fail, index:") != std::string::npos && message.find(", ret:") != std::string::npos;
}

std::string UrmaFailure668::GetName() const
{
    return "修改JFS执行失败导致修改JFS失败";
}

std::string UrmaFailure668::GetRootCauseDesc() const
{
    return "bondp_modify_jfs执行修改JFS时依赖的修改JFS步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure668::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure668::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure668::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_modify_jfs，modify pjfs fail, index:，, ret:。";
}

std::string UrmaFailure668::GetId() const
{
    return "urma_668";
}
} // namespace diag
