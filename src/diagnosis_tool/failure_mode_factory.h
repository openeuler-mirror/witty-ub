#pragma once
#include "failure_mode.h"
#include <memory>
#include <string>
#include <unordered_map>
#include <functional>
#include <vector>

namespace diag {
class FailureMode;

class FailureModeFactory {
public:
    using Creator = std::function<std::shared_ptr<FailureMode>()>;
    
    // 获取单例实例
    static FailureModeFactory& Instance();
    
    // 注册故障模式类型
    void Register(const std::string& typeId, Creator creator);
    
    // 创建故障模式实例
    std::shared_ptr<FailureMode> Create(const std::string& typeId) const;
    
    // 获取所有已注册的类型ID
    std::vector<std::string> GetAllTypeIds() const;
    
    // 检查是否已注册
    bool IsRegistered(const std::string& typeId) const;
    
private:
    FailureModeFactory() = default;
    std::unordered_map<std::string, Creator> m_creators;
};

// 自动注册辅助类模板，FailureMode派生类定义时必须构造该类
template<typename T>
class AutoRegister {
public:
    explicit AutoRegister(const std::string& typeId) {
        FailureModeFactory::Instance().Register(typeId, []() {
            return std::make_shared<T>();
        });
    }
};
}