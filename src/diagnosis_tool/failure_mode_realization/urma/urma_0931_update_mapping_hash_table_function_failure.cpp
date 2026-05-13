#include "urma_0931_update_mapping_hash_table_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0931UpdateMappingHashTableFunctionFailure> g_urma("urma_0931");

bool Urma0931UpdateMappingHashTableFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0932", "urma_0933", "urma_0934"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0931UpdateMappingHashTableFunctionFailure::GetName() const
{
    return "update_mapping_hash_table 函数故障";
}

std::string Urma0931UpdateMappingHashTableFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0931UpdateMappingHashTableFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0931UpdateMappingHashTableFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0931UpdateMappingHashTableFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0931UpdateMappingHashTableFunctionFailure::GetId() const
{
    return "urma_0931";
}
} // namespace diag
